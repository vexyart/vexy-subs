# this_file: src/vexy_subs/speakers.py
"""Temporal speaker attribution with explicit overlap ambiguity."""

from intervaltree import IntervalTree

from .types import Turn, Word


def assign(words: list[Word], turns: list[Turn]) -> None:
    """Choose maximum overlapping activity; retain flags for simultaneous speakers."""
    ordered = sorted(turns, key=lambda turn: turn.start)
    tree = IntervalTree.from_tuples((t.start, t.end, t.speaker) for t in ordered)
    for word in words:
        scores: dict[str, float] = {}
        end = max(word.end, word.start + 0.001)
        for turn in tree.overlap(word.start, end):
            overlap = max(0.0, min(end, turn.end) - max(word.start, turn.begin))
            if overlap:
                scores[turn.data] = scores.get(turn.data, 0) + overlap
        if scores:
            word.speaker = min(scores, key=lambda speaker: (-scores[speaker], speaker))
            word.ambiguous = len(scores) > 1
        else:
            midpoint = (word.start + word.end) / 2
            nearest = min(
                ordered,
                key=lambda t: min(abs(midpoint - t.start), abs(midpoint - t.end)),
                default=None,
            )
            if (
                nearest
                and min(abs(midpoint - nearest.start), abs(midpoint - nearest.end))
                <= 0.5
            ):
                word.speaker = nearest.speaker
    timed = [w for w in words if w.end > w.start]
    for word in words:
        if word.end != word.start or not timed:
            continue
        nearest = min(
            timed,
            key=lambda candidate: (
                max(candidate.start - word.start, word.start - candidate.end, 0),
                candidate.start < word.start,
            ),
        )
        word.speaker = nearest.speaker
        word.ambiguous = True
