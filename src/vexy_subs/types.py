# this_file: src/vexy_subs/types.py
"""Shared inference words/turns and subtitle-specific cues."""

from dataclasses import dataclass

from vexy_audioflexy.speech.types import Turn, Word

__all__ = ["Cue", "Turn", "Word"]


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    text: str
    speaker: str
