# this_file: src/vexy_subs/formats.py
"""Speaker colours in ASS, styled WebVTT and player-compatible SubRip."""

import colorsys
import html
from pathlib import Path

import pysubs2
import webvtt

from .types import Cue

PALETTE = (
    "#7DD3FC",
    "#FDE047",
    "#86EFAC",
    "#FDA4AF",
    "#C4B5FD",
    "#FDBA74",
    "#67E8F9",
    "#F0ABFC",
)


def timestamp(seconds: float) -> str:
    """Use the installed subtitle library's standard millisecond formatter."""
    from pysubs2.formats.subrip import SubripFormat

    return SubripFormat.ms_to_timestamp(round(seconds * 1000)).replace(",", ".")


def write(cues: list[Cue], stem: Path, speaker_names: dict | None = None) -> dict:
    """Write styled exports with one stable colour per session-local speaker ID."""
    ids = sorted({c.speaker for c in cues})
    names = speaker_names or {}
    colours = {}
    for index, speaker in enumerate(ids):
        rgb = colorsys.hsv_to_rgb((index * 0.61803398875) % 1, 0.4, 1)
        extra = "#" + "".join(f"{round(c * 255):02X}" for c in rgb)
        colours[speaker] = PALETTE[index] if index < len(PALETTE) else extra
    if "unassigned" in colours:
        colours["unassigned"] = "#FFFFFF"
    subs = pysubs2.SSAFile()
    subs.info.update(PlayResX="1920", PlayResY="1080")
    vtt = webvtt.WebVTT()
    for index, speaker in enumerate(ids):
        colour = colours[speaker]
        rgb = tuple(int(colour[offset : offset + 2], 16) for offset in (1, 3, 5))
        subs.styles[speaker] = pysubs2.SSAStyle(
            fontname="Arial",
            fontsize=46,
            primarycolor=pysubs2.Color(*rgb),
            outline=3,
            shadow=1,
            marginv=50,
        )
        vtt.styles.append(
            webvtt.Style(f"::cue(.speaker{index}) {{ color: {colour}; }}")
        )
    for cue in cues:
        name = names.get(cue.speaker, cue.speaker)
        subs.events.append(
            pysubs2.SSAEvent(
                start=round(cue.start * 1000),
                end=round(cue.end * 1000),
                text=cue.text.replace("\n", r"\N"),
                style=cue.speaker,
                name=name,
            )
        )
        index = ids.index(cue.speaker)
        text = f"<v {html.escape(name, quote=True)}><c.speaker{index}>{html.escape(cue.text)}</c></v>"
        vtt.captions.append(
            webvtt.Caption(timestamp(cue.start), timestamp(cue.end), text)
        )
    subs.save(str(stem) + ".ass")
    vtt.save(str(stem) + ".vtt")
    coloured = pysubs2.SSAFile()
    coloured.events = [
        pysubs2.SSAEvent(
            start=round(c.start * 1000),
            end=round(c.end * 1000),
            text=f'<font color="{colours[c.speaker]}">{html.escape(c.text, quote=False)}</font>',
        )
        for c in cues
    ]
    coloured.save(str(stem) + ".srt", apply_styles=False)
    return {
        speaker: {"label": names.get(speaker, speaker), "color": colours[speaker]}
        for speaker in ids
    }


def verify(stem: Path, duration: float) -> dict:
    """Independently parse all three formats, retaining voice and colour evidence."""
    srt = pysubs2.load(str(stem) + ".srt", format_="srt")
    ass = pysubs2.load(str(stem) + ".ass", format_="ass")
    vtt = webvtt.read(str(stem) + ".vtt")
    if not len(srt) == len(ass) == len(vtt):
        raise ValueError("Export cue counts differ")
    previous = 0
    for a, b, c in zip(srt, ass, vtt, strict=True):
        if html.unescape(a.plaintext) != b.plaintext or b.plaintext != html.unescape(
            c.text
        ):
            raise ValueError("Styled exports lost or changed text")
        if not 0 <= a.start < a.end <= duration * 1000 + 100 or a.start < previous:
            raise ValueError("Invalid subtitle timeline")
        if abs(a.start - b.start) > 10 or abs(a.end - b.end) > 10:
            raise ValueError("ASS timing differs beyond its centisecond precision")
        if not c.voice or b.style not in ass.styles:
            raise ValueError("Missing speaker styling")
        previous = a.end
    return {
        "cues": len(srt),
        "speakers": len({s.style for s in ass}),
        "vtt_styles": len(vtt.styles),
        "last_end": previous / 1000,
    }
