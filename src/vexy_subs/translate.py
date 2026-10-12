# this_file: src/vexy_subs/translate.py
"""Two-pass LLM subtitle translation that keeps every cue's timing and style.

Pass 1 translates a chunk of cues with the glossary and the previous translated
chunk as context; pass 2 refines the wording. Cues travel as ``{"id", "text"}``
JSON, so multi-line cues stay whole and a dropped or merged cue is rejected and
retried instead of shifting later timestamps.
"""

import asyncio
import copy
import json
from dataclasses import dataclass, field
from pathlib import Path

import pysubs2
from loguru import logger
from pysubs2.exceptions import FormatAutodetectionError

from .llm import Endpoint, ask_json, load_env, read_config, resolve_all, spec_text

CHUNK_SIZE = 40
_FORMATS = {".vtt": "vtt", ".srt": "srt", ".ass": "ass", ".ssa": "ssa"}


@dataclass
class Subtitle:
    """One cue: milliseconds avoid float drift; ``text`` is plain, ``\\n`` between lines."""

    start_ms: int
    end_ms: int
    text: str


@dataclass
class SubtitleFile:
    """Parsed cues plus the original pysubs2 file, kept to preserve styles on save."""

    events: list[Subtitle]
    format: str = "srt"
    source_path: str | None = None
    ssa: pysubs2.SSAFile | None = field(default=None, repr=False, compare=False)
    recognized: bool = field(default=True, repr=False, compare=False)


def format_for(path: str | Path, default: str = "srt") -> str:
    """Subtitle format from the file extension."""
    return _FORMATS.get(Path(path).suffix.lower(), default)


def load_subtitles(path: str | Path) -> SubtitleFile:
    """Load SRT/VTT/ASS/SSA; an empty or unrecognisable file loads with no cues."""
    source = Path(path)
    fmt = format_for(source)
    try:
        ssa = pysubs2.load(str(source))
    except FormatAutodetectionError:
        return SubtitleFile([], fmt, str(source), recognized=False)
    events = [e for e in ssa.events if not e.is_comment]
    ssa.events = events
    cues = [Subtitle(e.start, e.end, e.plaintext) for e in events]
    return SubtitleFile(cues, fmt, str(source), ssa)


def save_subtitles(
    subtitle_file: SubtitleFile, path: str | Path, fmt: str | None = None
) -> None:
    """Write cues; the format follows ``fmt``, else the extension of ``path``.

    When the file came from :func:`load_subtitles` with the same cue count, its
    styles and per-cue style/speaker fields are kept by position and only
    times/text change; set ``ssa=None`` after reordering or replacing cues. Text
    goes through pysubs2's ``plaintext``, so ``{...}`` reads as an ASS override
    tag and is lost.
    """
    target = Path(path)
    output = fmt or format_for(target, subtitle_file.format)
    original = subtitle_file.ssa
    if original is not None and len(original.events) == len(subtitle_file.events):
        ssa = copy.deepcopy(original)
    else:
        ssa = pysubs2.SSAFile()
        ssa.events = [pysubs2.SSAEvent() for _ in subtitle_file.events]
    for event, cue in zip(ssa.events, subtitle_file.events, strict=True):
        event.start, event.end = cue.start_ms, cue.end_ms
        event.plaintext = cue.text
    target.parent.mkdir(parents=True, exist_ok=True)
    ssa.save(str(target), format_=output)


def chunk_subtitles(
    events: list[Subtitle], chunk_size: int = CHUNK_SIZE
) -> list[list[Subtitle]]:
    """Split cues into groups: enough context for the model, few enough to keep counts exact."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    return [events[i : i + chunk_size] for i in range(0, len(events), chunk_size)]


def load_vocabulary(path: str | Path | None) -> dict[str, str]:
    """Glossary JSON ``{"source term": "target term"}``; no path means no glossary."""
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in data.items()
    ):
        raise ValueError(f"Vocabulary must be a JSON object of strings: {path}")
    return data


_REPLY = (
    'Return ONLY JSON {"cues":[{"id":0,"text":"..."},...]} with exactly the same ids, '
    "in the same order, one entry per input cue. Keep line breaks (\\n) inside a cue "
    "where natural. Never merge, split, drop or add cues."
)


def translation_prompt(
    source_lang: str,
    target_lang: str,
    vocabulary: dict[str, str],
    previous: list[Subtitle] | None,
) -> str:
    """System prompt for pass 1: glossary and previous translated cues as context."""
    parts = [f"Translate these subtitle cues from {source_lang} to {target_lang}."]
    if vocabulary:
        terms = "\n".join(f"{k} → {v}" for k, v in vocabulary.items())
        parts.append(f"Use this terminology exactly as written:\n{terms}")
    if previous:
        context = "\n".join(cue.text for cue in previous)
        parts.append(f"For context, the previously translated cues were:\n{context}")
    parts.append(_REPLY)
    return "\n\n".join(parts)


def refinement_prompt(source_lang: str, target_lang: str) -> str:
    """System prompt for pass 2: fix literal phrasing without changing meaning."""
    return (
        f"Review and refine these {target_lang} subtitle translations (originally "
        f"{source_lang}). Fix stiff literal phrasing, improve coherence and make the "
        f"language natural without changing meaning.\n\n{_REPLY}"
    )


def _checker(expected: list[int]):
    """Accept only replies that return every id once, in order, with non-empty text."""

    def check(reply: object) -> list[str]:
        cues = reply.get("cues") if isinstance(reply, dict) else None
        if not isinstance(cues, list):
            raise ValueError('LLM reply lacks a "cues" list')  # noqa: TRY004  (a bad reply, not a caller bug)
        ids = [c.get("id") if isinstance(c, dict) else None for c in cues]
        if ids != expected:
            raise ValueError(
                f"LLM returned cue ids {ids[:5]}..., expected {len(expected)} in order"
            )
        texts = [c.get("text") for c in cues]
        if not all(isinstance(t, str) and t.strip() for t in texts):
            raise ValueError("LLM returned an empty or non-string cue")
        return [t.strip() for t in texts]

    return check


def _pass(
    endpoints: list[Endpoint], system: str, texts: list[str], timeout: float
) -> list[str]:
    """One LLM pass; a chunk whose replies keep failing validation is halved."""
    payload = {"cues": [{"id": i, "text": t} for i, t in enumerate(texts)]}
    try:
        return ask_json(
            endpoints, system, payload, _checker(list(range(len(texts)))), timeout
        )
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        if len(texts) < 2:
            raise
        half = len(texts) // 2
        logger.warning("Splitting {} cues after: {}", len(texts), exc)
        return _pass(endpoints, system, texts[:half], timeout) + _pass(
            endpoints, system, texts[half:], timeout
        )


def translate_events(
    events: list[Subtitle],
    endpoints: list[Endpoint],
    source_lang: str,
    target_lang: str,
    vocabulary: dict[str, str] | None = None,
    chunk_size: int = CHUNK_SIZE,
    refine: bool = True,
    timeout: float = 60,
) -> list[Subtitle]:
    """Translate cues chunk by chunk; timings are copied from the source cues."""
    result: list[Subtitle] = []
    previous: list[Subtitle] | None = None
    chunks = chunk_subtitles(events, chunk_size)
    for index, chunk in enumerate(chunks, 1):
        logger.info("Translating chunk {}/{} ({} cues)", index, len(chunks), len(chunk))
        system = translation_prompt(
            source_lang, target_lang, vocabulary or {}, previous
        )
        texts = _pass(endpoints, system, [c.text for c in chunk], timeout)
        if refine:
            texts = _pass(
                endpoints, refinement_prompt(source_lang, target_lang), texts, timeout
            )
        previous = [
            Subtitle(c.start_ms, c.end_ms, t) for c, t in zip(chunk, texts, strict=True)
        ]
        result.extend(previous)
    return result


def translate_file(
    subtitle_file: SubtitleFile,
    llm_spec: str,
    source_lang: str,
    target_lang: str,
    vocab_path: str | None = None,
    config_file: str = "",
    chunk_size: int = CHUNK_SIZE,
    refine: bool = True,
    timeout: float = 60,
) -> SubtitleFile:
    """Resolve the LLM spec and glossary, then translate a whole file."""
    endpoints = resolve_all(llm_spec, read_config(config_file) if config_file else None)
    events = translate_events(
        subtitle_file.events,
        endpoints,
        source_lang,
        target_lang,
        load_vocabulary(vocab_path),
        chunk_size,
        refine,
        timeout,
    )
    return SubtitleFile(
        events, subtitle_file.format, subtitle_file.source_path, subtitle_file.ssa
    )


def translate_subtitles_sync(
    subtitle_file: SubtitleFile,
    llm_spec: str,
    source_lang: str,
    target_lang: str,
    vocab_path: str | None = None,
) -> SubtitleFile:
    """vttrix-compatible blocking API."""
    return translate_file(subtitle_file, llm_spec, source_lang, target_lang, vocab_path)


async def translate_subtitles(
    subtitle_file: SubtitleFile,
    llm_spec: str,
    source_lang: str,
    target_lang: str,
    vocab_path: str | None = None,
) -> SubtitleFile:
    """vttrix-compatible async API; the blocking HTTP calls run in a worker thread."""
    return await asyncio.to_thread(
        translate_file, subtitle_file, llm_spec, source_lang, target_lang, vocab_path
    )


def run(
    src: str,
    dst: str,
    llm: str,
    source_lang: str,
    target_lang: str,
    vocab: str = "",
    config_file: str = "",
    env_file: str = "",
    chunk_size: int = CHUNK_SIZE,
    refine: bool = True,
    timeout: float = 60,
    force: bool = False,
) -> dict:
    """Translate a subtitle file; the output extension picks SRT, VTT or ASS.

    ``llm`` is a profile name, ``model::ENV_KEY::base_url``, or a comma-separated
    fallback list. ``vocab`` is a JSON glossary of exact term translations.
    Keys may come from ``--env_file``, a working-directory ``.env`` or the
    ``.env`` beside the config file.
    """
    target = Path(dst)
    if target.exists() and not force:
        raise FileExistsError(f"{target} exists; use --force to overwrite")
    if Path(src).resolve() == target.resolve():
        raise ValueError("Output would overwrite the input")
    if vocab and not Path(vocab).is_file():
        raise FileNotFoundError(vocab)
    load_env(env_file, config_file)
    endpoints = resolve_all(
        spec_text(llm), read_config(config_file) if config_file else None
    )
    subs = load_subtitles(src)
    if not subs.recognized and Path(src).read_text(errors="replace").strip():
        raise ValueError(f"No subtitle cues could be parsed from {src}")
    events = translate_events(
        subs.events,
        endpoints,
        source_lang,
        target_lang,
        load_vocabulary(vocab or None),
        chunk_size,
        refine,
        timeout,
    )
    save_subtitles(
        SubtitleFile(events, subs.format, subs.source_path, subs.ssa), target
    )
    return {
        "input": src,
        "output": str(target),
        "format": format_for(target, subs.format),
        "cues": len(events),
        "source_lang": source_lang,
        "target_lang": target_lang,
        "llm": [e.receipt() for e in endpoints],
        "refined": refine,
    }
