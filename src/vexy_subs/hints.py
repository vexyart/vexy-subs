# this_file: src/vexy_subs/hints.py
"""User-owned UTF-8 recognition hints; never bundled into distributions."""

import hashlib
from pathlib import Path

# Tagged recording metadata reaches ASR even when a Names:/Terms: glossary exists.
METADATA = ("Title:", "Description:")
REFERENCE_MARGIN = 1.5


def read_prompt(prompt_file: str = "", prompt: str = "") -> tuple[str, dict]:
    """Accept .md or .txt, and record its digest without leaking its contents."""
    if not prompt_file:
        return prompt, {"sha256": hashlib.sha256(prompt.encode()).hexdigest()}
    path = Path(prompt_file)
    if path.suffix.lower() not in {".md", ".txt"}:
        raise ValueError("prompt_file must be a UTF-8 .md or .txt file")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("prompt_file is empty")
    return "\n".join(filter(None, (prompt, text))), {
        "filename": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def vocabulary(prompt: str) -> list[str]:
    """Use optional Names:/Terms: lines for casing; free-form hints still reach ASR."""
    terms = []
    for line in prompt.splitlines():
        if line.startswith(("Names:", "Terms:")):
            terms.extend(
                t.strip().rstrip(".") for t in line.split(":", 1)[1].split(",")
            )
    return [t for t in terms if t]


def metadata(prompt: str) -> str:
    """Return tagged Title:/Description: lines, which describe but are not speech."""
    return "\n".join(line for line in prompt.splitlines() if line.startswith(METADATA))


def read_reference(reference_file: str = "") -> tuple[list[tuple], dict]:
    """Load a human-edited SRT/WebVTT transcript as timed reference text."""
    if not reference_file:
        return [], {}
    import pysubs2

    path = Path(reference_file)
    events = [
        (e.start / 1000, e.end / 1000, " ".join(e.plaintext.split()))
        for e in pysubs2.load(str(path))
        if e.plaintext.strip()
    ]
    if not events:
        raise ValueError("reference_file contains no caption text")
    return events, {
        "filename": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def excerpt(reference: list[tuple], start: float, end: float) -> str:
    """Only the reference text overlapping one audio chunk, never the whole talk."""
    lines = []
    for first, last, text in reference:
        overlaps = first < end + REFERENCE_MARGIN and last > start - REFERENCE_MARGIN
        if overlaps and (not lines or lines[-1] != text):
            lines.append(text)
    return " ".join(lines)
